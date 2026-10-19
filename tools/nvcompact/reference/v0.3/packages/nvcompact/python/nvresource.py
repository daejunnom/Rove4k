#!/usr/bin/env python3
"""Plan large-resource UCI checks without launching an engine; run only with --start.

This is a bounded execution aid, not a sandbox or a memory reservation service.
The input artifact and embedded resource constants are never rewritten.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import sys
import time

import nvuci


SPEC_FORMAT = "nvcompact.resource-spec.v1"
PLAN_FORMAT = "nvcompact.resource-plan.v1"
RUN_FORMAT = "nvcompact.resource-run.v1"
JSON_LIMIT = 1 << 20

# Limits are lowered in the newly spawned Python exec wrapper, never in the
# caller. No preexec_fn is used in a potentially multithreaded parent process.
LIMITED_EXEC = """import json,os,resource,sys
limits=json.loads(sys.argv[1])
for name,value in limits.items():
    kind=getattr(resource,name)
    soft,hard=resource.getrlimit(kind)
    if (soft!=resource.RLIM_INFINITY and soft<value) or (hard!=resource.RLIM_INFINITY and hard<value):
        raise SystemExit('inherited '+name+' is below the approved plan; regenerate the plan')
    resource.setrlimit(kind,(value,value))
os.execv(sys.argv[2],sys.argv[3:])
"""


def _json(path: Path) -> dict:
    if path.stat().st_size > JSON_LIMIT:
        raise ValueError("JSON input exceeds one MiB: " + str(path))
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("JSON input must be an object")
    return value


def _digest(value: dict) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(data).hexdigest()


def _fingerprint(path: Path, role: str) -> dict:
    path = path.resolve(strict=True)
    if not path.is_file():
        raise ValueError("expected a regular input file: " + str(path))
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    state = path.stat()
    return {"role": role, "path": str(path), "bytes": state.st_size,
            "mode": state.st_mode & 0o777, "sha256": digest.hexdigest()}


def _write_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _read_number(path: Path) -> int | None:
    value = path.read_text().strip()
    return None if value == "max" else int(value)


def _fields(path: Path) -> dict[str, int]:
    return {parts[0].rstrip(":"): int(parts[1])
            for line in path.read_text().splitlines() if len(parts := line.split()) >= 2}


def _mount_path(value: str) -> str:
    for old, new in (("\\040", " "), ("\\011", "\t"), ("\\012", "\n"), ("\\134", "\\")):
        value = value.replace(old, new)
    return value


def probe_resources(proc_root: Path = Path("/proc")) -> dict:
    """Read host/current-cgroup facts; never allocate a test block or run tools.

    Inactive file pages are a reclaim estimate, not reserved free memory. The
    raw headroom is retained so this assumption is visible in every report.
    """
    facts = {"platform": sys.platform, "memory": {}, "cgroup_v2": [], "errors": []}
    try:
        memory = _fields(proc_root / "meminfo")
        facts["memory"] = {"physical_total_bytes": memory["MemTotal"] * 1024,
                           "physical_available_bytes": memory["MemAvailable"] * 1024}
    except (OSError, KeyError, ValueError) as exc:
        facts["errors"].append("physical memory observation unavailable: " + str(exc))
    try:
        facts["affinity_cpu_count"] = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        facts["affinity_cpu_count"] = None
    try:
        facts["proc_pid_namespace_matches"] = int((proc_root / "self/stat").read_text().split()[0]) == os.getpid()
    except (OSError, ValueError, IndexError):
        facts["proc_pid_namespace_matches"] = None
    try:
        memberships = (proc_root / "self/cgroup").read_text().splitlines()
        unified = next((line.split(":", 2)[2] for line in memberships if line.startswith("0::")), None)
        memory_v1 = any("memory" in line.split(":", 2)[1].split(",") for line in memberships)
        if unified is None and memory_v1:
            facts["errors"].append("cgroup v1 memory accounting is unsupported; use a v2 or unconfined test host")
        if unified is not None:
            locations = []
            for line in (proc_root / "self/mountinfo").read_text().splitlines():
                fields, separator, tail = line.partition(" - ")
                if not separator or tail.split()[0] != "cgroup2":
                    continue
                fields = fields.split()
                mount_root = Path(_mount_path(fields[3]))
                mount_at = Path(_mount_path(fields[4]))
                membership = Path(unified)
                if membership.is_relative_to(mount_root):
                    locations.append((mount_at / membership.relative_to(mount_root), mount_at))
            if not locations:
                facts["errors"].append("current cgroup v2 mount could not be resolved")
            seen = set()
            for current, mount_at in locations:
                while True:
                    if str(current) not in seen:
                        seen.add(str(current))
                        limit_path = current / "memory.max"
                        usage_path = current / "memory.current"
                        if limit_path.exists() != usage_path.exists():
                            facts["errors"].append("incomplete cgroup memory files: " + str(current))
                        elif limit_path.exists():
                            cap, usage = _read_number(limit_path), _read_number(usage_path)
                            if usage is None or usage < 0 or (cap is not None and cap < 0):
                                raise ValueError("invalid cgroup memory amount")
                            stat_path = current / "memory.stat"
                            stat = _fields(stat_path) if stat_path.exists() else {}
                            inactive = max(0, min(stat.get("inactive_file", 0), stat.get("file", 0), usage))
                            item = {"path": str(current), "memory_max_bytes": cap,
                                    "memory_current_bytes": usage, "inactive_file_bytes": inactive,
                                    "raw_headroom_bytes": None if cap is None else max(0, cap - usage),
                                    "estimated_available_bytes": None if cap is None else max(0, cap - max(0, usage - inactive))}
                            cpu_path = current / "cpu.max"
                            if cpu_path.exists():
                                item["cpu_max"] = cpu_path.read_text().strip()
                            facts["cgroup_v2"].append(item)
                    if current == mount_at:
                        break
                    if not current.is_relative_to(mount_at) or current.parent == current:
                        raise ValueError("cgroup path escaped its observed mount")
                    current = current.parent
    except (OSError, ValueError, IndexError) as exc:
        facts["errors"].append("cgroup observation unavailable: " + str(exc))
    facts["rlimits"] = {name: list(resource.getrlimit(getattr(resource, name)))
                        for name in ("RLIMIT_AS", "RLIMIT_CPU", "RLIMIT_FSIZE", "RLIMIT_CORE")}
    available = [facts["memory"].get("physical_available_bytes")]
    available += [item["estimated_available_bytes"] for item in facts["cgroup_v2"]]
    available = [item for item in available if item is not None]
    facts["estimated_available_memory_bytes"] = min(available) if available else None
    facts["memory_estimate_scope"] = "min(physical MemAvailable, each cgroup max-current+inactive_file); transient reclaim estimate, not allocation success or a reservation"
    return facts


def _limits(budget: dict) -> dict:
    return {"RLIMIT_AS": budget["address_space_bytes"],
            "RLIMIT_CPU": budget["cpu_seconds_per_process"],
            "RLIMIT_FSIZE": budget["file_bytes"], "RLIMIT_CORE": 0}


def _validate_budget(budget: dict) -> None:
    for key in ("required_memory_bytes", "reserve_memory_bytes", "address_space_bytes",
                "cpu_seconds_per_process", "file_bytes", "output_bytes_per_session"):
        value = budget.get(key)
        minimum = 0 if key == "reserve_memory_bytes" else 1
        if type(value) is not int or not minimum <= value <= (1 << 63) - 1:
            raise ValueError("budget." + key + " must be a finite signed-64-bit integer >= " + str(minimum))
    if budget["address_space_bytes"] < budget["required_memory_bytes"]:
        raise ValueError("address-space cap is below the declared memory requirement")
    wall = budget.get("wall_seconds")
    if isinstance(wall, bool) or not isinstance(wall, (int, float)) or not math.isfinite(wall) or wall <= 0:
        raise ValueError("budget.wall_seconds must be positive and finite")


def preflight(plan: dict, facts: dict) -> dict:
    reasons = list(facts["errors"])
    if facts["platform"] != "linux":
        reasons.append("resource execution currently supports Linux")
    budget = plan["budget"]
    needed = budget["required_memory_bytes"] + budget["reserve_memory_bytes"]
    available = facts["estimated_available_memory_bytes"]
    if available is None or available < needed:
        reasons.append("declared memory plus reserve exceeds the observed available estimate")
    for name, required in _limits(budget).items():
        soft, hard = facts["rlimits"][name]
        if any(value != resource.RLIM_INFINITY and value < required for value in (soft, hard)):
            reasons.append("inherited " + name + " is below the planned limit; it will not be raised")
    for item in plan["tools"]:
        if not item["path"]:
            reasons.append("declared tool is missing: " + item["name"])
    return {"status": "blocked" if reasons else "ready", "reasons": reasons,
            "declared_required_plus_reserve_bytes": needed,
            "estimated_available_memory_bytes": available,
            "scope": "read-only prerequisites; ready does not mean the engine has run or passed"}


def create_plan(spec_path: Path) -> dict:
    spec_path = spec_path.resolve(strict=True)
    spec = _json(spec_path)
    if spec.get("format") != SPEC_FORMAT:
        raise ValueError("unsupported resource specification format")
    pins = [_fingerprint(spec_path, "specification")]
    manifest = None
    if "manifest" in spec:
        manifest_path = (spec_path.parent / spec["manifest"]).resolve(strict=True)
        manifest = _json(manifest_path)
        artifact = (manifest_path.parent / manifest["artifact"]).absolute()
        pins.append(_fingerprint(manifest_path, "engine_manifest"))
    elif "artifact" in spec:
        artifact = (spec_path.parent / spec["artifact"]).absolute()
    else:
        raise ValueError("specification needs an artifact or engine manifest")
    artifact_pin = _fingerprint(artifact, "artifact")
    expected = manifest.get("sha256") if manifest else spec.get("sha256")
    if expected and artifact_pin["sha256"] != expected:
        raise ValueError("artifact does not match the declared SHA256")
    pins.append(artifact_pin)
    command = spec.get("command", ["{artifact}"])
    if not isinstance(command, list) or not command or not all(isinstance(arg, str) and arg and "\0" not in arg for arg in command):
        raise ValueError("command must be a nonempty argv array")
    command = [arg.replace("{artifact}", str(artifact)) for arg in command]
    executable = shutil.which(command[0]) if not Path(command[0]).is_absolute() else command[0]
    if not executable or not os.access(executable, os.X_OK):
        raise ValueError("command executable is unavailable; no implicit shell is added")
    # Resolve which file to execute without changing argv[0] or a symlink
    # invocation name: applets and other programs may observe either one.
    executable = str(Path(executable).absolute())
    pins += [_fingerprint(Path(executable), "command_executable"),
             _fingerprint(Path(sys.executable), "python_executable"),
             _fingerprint(Path(__file__), "resource_runner"),
             _fingerprint(Path(nvuci.__file__), "uci_verifier")]
    tools = []
    if not isinstance(spec.get("tools", []), list):
        raise ValueError("tools must be an array")
    for name in spec.get("tools", []):
        if not isinstance(name, str) or not name or "\0" in name:
            raise ValueError("tools must contain executable names or paths")
        found = shutil.which(name)
        resolved = str(Path(found).resolve(strict=True)) if found else None
        tools.append({"name": name, "path": resolved})
        if found:
            pins.append(_fingerprint(Path(found), "declared_tool:" + name))
    budget = dict(spec.get("budget", {}))
    _validate_budget(budget)
    wall = budget["wall_seconds"]
    settings = {"preserve_engine_options": True, **spec.get("uci", {})}
    if "artifact_path" in settings:
        raise ValueError("uci.artifact_path is derived from the selected artifact")
    if "max_seconds" in settings and settings["max_seconds"] != wall:
        raise ValueError("uci.max_seconds must match budget.wall_seconds")
    settings["max_seconds"] = wall
    settings["artifact_path"] = artifact_pin["path"]
    settings.setdefault("max_output_bytes", budget["output_bytes_per_session"])
    if settings["max_output_bytes"] > budget["output_bytes_per_session"]:
        raise ValueError("UCI output cap exceeds the resource budget")
    if settings.get("oracle_path"):
        settings["oracle_path"] = str((spec_path.parent / settings["oracle_path"]).resolve(strict=True))
    config = nvuci.Config(**settings)
    config.validate()
    facts = probe_resources()
    plan = {"format": PLAN_FORMAT, "status": "planned", "engine_started": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "name": spec.get("name", artifact.name), "command": command,
            "executable_path": executable, "artifact_path": str(artifact),
            "artifact": artifact_pin, "inputs": pins, "tools": tools,
            "budget": budget, "uci_configuration": asdict(config),
            "specification": spec,
            "previous_runtime_blocked": manifest.get("runtime_blocked") if manifest else None,
            "resources_at_plan": facts,
            "engine_option_policy": "preserve advertised defaults and embedded constants" if config.preserve_engine_options else "explicitly configured UCI options; this is a different execution configuration",
            "scope": {"execution": "target was not executed; no allocation probe or compiler/version command ran",
                      "limits": "inherited per-process AS/CPU/file limits; verifier wall/output budgets; no per-job hard resident-memory or aggregate CPU cgroup is created",
                      "cleanup": "original engine process group; escaped independent sessions are outside the harness scope",
                      "memory": "declared requirement and reserve are explicit assumptions; available memory is not reserved"}}
    plan["preflight_at_plan"] = preflight(plan, facts)
    plan["plan_sha256"] = _digest(plan)
    return plan


def _changed_inputs(plan: dict) -> list[dict]:
    changed = []
    executing = {"artifact": Path(plan["artifact_path"]),
                 "command_executable": Path(plan["executable_path"]),
                 "python_executable": Path(sys.executable), "resource_runner": Path(__file__),
                 "uci_verifier": Path(nvuci.__file__)}
    for expected in plan["inputs"]:
        try:
            actual = _fingerprint(Path(expected["path"]), expected["role"])
        except (OSError, ValueError) as exc:
            changed.append({"role": expected["role"], "path": expected["path"], "error": str(exc)})
            continue
        if actual != expected:
            changed.append({"role": expected["role"], "expected": expected, "actual": actual})
        if expected["role"] in executing:
            try:
                running = _fingerprint(executing[expected["role"]], expected["role"])
            except (OSError, ValueError) as exc:
                changed.append({"role": "executing_" + expected["role"],
                                "path": str(executing[expected["role"]]), "error": str(exc)})
                continue
            if running != expected:
                changed.append({"role": "executing_" + expected["role"], "expected": expected, "actual": running})
    for item in plan["tools"]:
        resolved = shutil.which(item["name"])
        actual = str(Path(resolved).resolve(strict=True)) if resolved else None
        if actual != item["path"]:
            changed.append({"role": "tool_resolution", "tool": item["name"], "expected": item["path"], "actual": actual})
    return changed


def execute_plan(plan_path: Path, output: Path, *, start: bool = False) -> dict:
    if start is not True:
        raise ValueError("explicit --start is required; planning does not authorize execution")
    plan_path = plan_path.resolve(strict=True)
    plan = _json(plan_path)
    if plan.get("format") != PLAN_FORMAT or plan.get("status") != "planned":
        raise ValueError("expected a resource plan")
    unsigned = {key: value for key, value in plan.items() if key != "plan_sha256"}
    if _digest(unsigned) != plan.get("plan_sha256"):
        raise ValueError("plan checksum changed; regenerate the plan from its specification")
    _validate_budget(plan["budget"])
    config = nvuci.Config(**plan["uci_configuration"])
    config.validate()
    if config.artifact_path != plan["artifact"]["path"]:
        raise ValueError("the UCI artifact differs from the pinned artifact")
    if config.max_seconds != plan["budget"]["wall_seconds"] or config.max_output_bytes > plan["budget"]["output_bytes_per_session"]:
        raise ValueError("plan configuration exceeds or differs from the declared execution budget")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    facts = probe_resources()
    changes = _changed_inputs(plan)
    before_environment = dict(os.environ)
    report = {"format": RUN_FORMAT, "status": "blocked", "engine_started": False,
              "started_at": datetime.now(timezone.utc).isoformat(),
              "plan_sha256": plan["plan_sha256"], "plan": plan,
              "resources_before": facts, "preflight": preflight(plan, facts),
              "changed_inputs_before": changes, "uci": None}
    started = time.monotonic()
    _write_new(output / "plan.json", plan)
    if changes:
        report["preflight"]["status"] = "blocked"
        report["preflight"]["reasons"].append("a pinned input or tool resolution changed; regenerate the plan")
    if report["preflight"]["status"] == "ready":
        limits = _limits(plan["budget"])
        command = [str(Path(sys.executable).absolute()), "-B", "-c", LIMITED_EXEC,
                   json.dumps(limits, sort_keys=True), plan["executable_path"], *plan["command"]]
        report["launch_command"] = command
        report["requested_rlimits"] = limits
        report["status"] = "running"
        # An interrupt or exception may arrive after process creation but before
        # verify_engine returns its observations. Do not label that as no run.
        report["engine_started"] = None
        try:
            result = nvuci.verify_engine(command, config)
            report["uci"] = result
            report["engine_launch_attempted"] = bool(result.get("sessions"))
            report["engine_started"] = True if result.get("handshakes") else None if result.get("sessions") else False
            report["status"] = result["verdict"]
            _write_new(output / "uci.json", result)
        except (OSError, ValueError, TypeError) as exc:
            report.update(status="error", error=str(exc))
        except BaseException as exc:
            # nvuci's finally closes its owned process group. The public CLI
            # launcher also tracks process creation and owns signal cleanup.
            report.update(status="interrupted", error=type(exc).__name__)
            raise
        finally:
            report["changed_inputs_after"] = _changed_inputs(plan)
            if report["changed_inputs_after"] and report["status"] != "interrupted":
                report["status"] = "fail"
                report["input_preservation_error"] = "an input changed during execution; no automatic restoration was attempted"
            report["environment_unchanged"] = dict(os.environ) == before_environment
            report["resources_after"] = probe_resources()
            report["elapsed_seconds"] = round(time.monotonic() - started, 6)
            _write_new(output / "result.json", report)
    else:
        report["environment_unchanged"] = dict(os.environ) == before_environment
        report["elapsed_seconds"] = round(time.monotonic() - started, 6)
        _write_new(output / "result.json", report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    planning = sub.add_parser("plan", help="read files/resources and save a plan; never run the target")
    planning.add_argument("specification", type=Path)
    planning.add_argument("--output", type=Path, required=True)
    running = sub.add_parser("run", help="execute a previously saved plan only after --start")
    running.add_argument("plan", type=Path)
    running.add_argument("--start", action="store_true")
    running.add_argument("--output", type=Path, required=True, help="new directory; existing results are never overwritten")
    args = parser.parse_args(argv)
    try:
        if args.operation == "plan":
            result = create_plan(args.specification)
            _write_new(args.output, result)
        else:
            result = execute_plan(args.plan, args.output, start=args.start)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] in ("planned", "pass") else 2
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("nvresource: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    if globals().get("_NVCOMPACT_MANAGED"):
        raise SystemExit(main())
    import nvlaunch
    raise SystemExit(nvlaunch.main(["resource", *sys.argv[1:]]))
